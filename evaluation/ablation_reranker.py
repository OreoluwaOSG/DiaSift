"""
Reranker ablation for Diasift retrieval (dissertation Section 3.5.2).

Compares the production hybrid reranking (semantic score + keyword overlap +
intent-aware rules, see scripts/search_test.py:rerank_results) against raw
ChromaDB vector-score ordering, on the existing production 900-character
baseline index, using the same 36 questions in eval_questions.json. This
script only reads the existing collection - it does not rebuild or modify
the vectorstore.

Usage:
    python3 evaluation/ablation_reranker.py
"""

from pathlib import Path
import json
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from search_test import (  # noqa: E402
    get_embedding_model,
    load_collection,
    normalize_question_text,
    rerank_results,
)

from run_retrieval_eval import first_hit_rank, load_eval_questions, summarize  # noqa: E402


def search_raw(question: str, number_of_results: int = 5) -> list[dict]:
    """Raw ChromaDB vector-score order: no lexical/intent reranking, no diversity cap."""
    model = get_embedding_model()
    collection = load_collection()

    normalized_question = normalize_question_text(question)
    question_embedding = model.encode([normalized_question]).tolist()

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=number_of_results,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    return [
        {"document": documents[index], "metadata": metadatas[index]}
        for index in range(len(documents))
    ]


def search_reranked(question: str, number_of_results: int = 5) -> list[dict]:
    """Production hybrid reranking, identical to scripts/search_test.py:search_documents."""
    model = get_embedding_model()
    collection = load_collection()

    normalized_question = normalize_question_text(question)
    question_embedding = model.encode([normalized_question]).tolist()
    candidate_count = min(max(number_of_results * 3, 10), collection.count())

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    return rerank_results(question, results, number_of_results)


def evaluate(search_fn, eval_questions: list[dict], max_k: int = 5) -> list[dict]:
    per_question_results = []

    for item in eval_questions:
        question = item["question"]
        expected_sources = item["expected_sources"]

        results = search_fn(question, max_k)
        retrieved_sources = [result["metadata"].get("source") for result in results]
        rank = first_hit_rank(expected_sources, retrieved_sources)

        per_question_results.append(
            {
                "question": question,
                "expected_sources": expected_sources,
                "retrieved_sources": retrieved_sources,
                "rank": rank,
                "reciprocal_rank": (1 / rank) if rank else 0,
                "hit_at_1": rank == 1,
                "hit_at_3": rank is not None and rank <= 3,
                "hit_at_5": rank is not None and rank <= 5,
            }
        )

    return per_question_results


def main() -> None:
    eval_questions = load_eval_questions()

    print("=" * 80)
    print("Raw vector search (reranking disabled)")
    print("=" * 80)
    raw_results = evaluate(search_raw, eval_questions)
    raw_summary = summarize(raw_results)
    print(json.dumps(raw_summary, indent=2))

    print("\n" + "=" * 80)
    print("Hybrid reranking (production baseline)")
    print("=" * 80)
    reranked_results = evaluate(search_reranked, eval_questions)
    reranked_summary = summarize(reranked_results)
    print(json.dumps(reranked_summary, indent=2))

    # Questions where reranking changed the outcome, in either direction.
    print("\n" + "=" * 80)
    print("Questions where reranking changed the result")
    print("=" * 80)
    changed = 0
    for raw, reranked in zip(raw_results, reranked_results):
        if raw["rank"] != reranked["rank"]:
            changed += 1
            print(f"\n- {raw['question']}")
            print(f"  raw rank:      {raw['rank']} | retrieved: {raw['retrieved_sources']}")
            print(f"  reranked rank: {reranked['rank']} | retrieved: {reranked['retrieved_sources']}")
    if not changed:
        print("(none)")

    output = {
        "raw_vector_search": {"summary": raw_summary, "results": raw_results},
        "hybrid_reranking": {"summary": reranked_summary, "results": reranked_results},
    }
    output_path = Path(__file__).resolve().parent / "reranker_ablation_results.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved full results to {output_path}")


if __name__ == "__main__":
    main()
