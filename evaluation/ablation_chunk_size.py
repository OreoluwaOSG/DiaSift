"""
Chunk size ablation for Diasift retrieval (dissertation Section 3.5.1).

Rebuilds the corpus at chunk_size in {600, 1300} into separate, temporary
ChromaDB collections and runs the same retrieval evaluation used for the
production baseline (evaluation/run_retrieval_eval.py) against each, using
the same 36 questions in eval_questions.json. The production 900-character
index and collection (diasift_type2_diabetes) are never touched - this
script only creates and deletes its own ablation collections.

Usage:
    python3 evaluation/ablation_chunk_size.py
"""

from pathlib import Path
import json
import sys

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ingest_documents import (  # noqa: E402
    RAW_DATA_DIR,
    clean_text,
    create_source_name,
    split_text_into_chunks,
)
from search_test import normalize_question_text, rerank_results  # noqa: E402

from run_retrieval_eval import first_hit_rank, load_eval_questions, summarize  # noqa: E402


VECTORSTORE_DIR = BASE_DIR / "vectorstore"
EMBEDDING_MODEL_NAME = "multi-qa-mpnet-base-dot-v1"
CHUNK_SIZES = [600, 1300]


def build_chunks(chunk_size: int) -> list[dict]:
    """Same logic as scripts/ingest_documents.py, parameterised by chunk_size."""
    txt_files = sorted(RAW_DATA_DIR.glob("*.txt"))
    all_chunks = []

    for file_path in txt_files:
        raw_text = file_path.read_text(encoding="utf-8")
        cleaned_text = clean_text(raw_text)
        chunks = split_text_into_chunks(cleaned_text, chunk_size=chunk_size)
        source_name = create_source_name(file_path)

        for index, chunk_text in enumerate(chunks, start=1):
            all_chunks.append(
                {
                    "chunk_id": f"{file_path.stem}_{index:03d}",
                    "source": source_name,
                    "source_file": file_path.name,
                    "chunk_index": index,
                    "text": chunk_text,
                }
            )

    return all_chunks


def build_collection(chunk_size: int, chunks: list[dict], model, client):
    """Same logic as scripts/build_index.py, writing to a throwaway collection."""
    collection_name = f"diasift_ablation_chunk{chunk_size}"

    existing_names = [
        collection.name if hasattr(collection, "name") else collection
        for collection in client.list_collections()
    ]

    if collection_name in existing_names:
        client.delete_collection(name=collection_name)

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "ip"},
    )

    ids, documents, documents_for_embedding, metadatas = [], [], [], []

    for chunk in chunks:
        ids.append(chunk["chunk_id"])
        documents.append(chunk["text"])
        documents_for_embedding.append(
            f"Source: {chunk['source']}\n"
            f"Document: {chunk['source_file']}\n\n"
            f"{chunk['text']}"
        )
        metadatas.append(
            {
                "source": chunk["source"],
                "source_file": chunk["source_file"],
                "chunk_index": chunk["chunk_index"],
            }
        )

    embeddings = model.encode(documents_for_embedding).tolist()
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    return collection, collection_name


def search(question: str, model, collection, number_of_results: int = 5):
    """Same search + rerank logic as scripts/search_test.py:search_documents."""
    normalized_question = normalize_question_text(question)
    question_embedding = model.encode([normalized_question]).tolist()
    candidate_count = min(max(number_of_results * 3, 10), collection.count())

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    return rerank_results(question, results, number_of_results)


def evaluate(collection, model, eval_questions: list[dict], max_k: int = 5) -> list[dict]:
    per_question_results = []

    for item in eval_questions:
        question = item["question"]
        expected_sources = item["expected_sources"]

        results = search(question, model, collection, number_of_results=max_k)
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

    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    all_results = {}

    for chunk_size in CHUNK_SIZES:
        print(f"\n{'=' * 80}\nChunk size: {chunk_size}\n{'=' * 80}")

        chunks = build_chunks(chunk_size)
        print(f"Built {len(chunks)} chunks")

        collection, collection_name = build_collection(chunk_size, chunks, model, client)
        print(f"Indexed into temporary collection: {collection_name}")

        per_question_results = evaluate(collection, model, eval_questions)
        summary = summarize(per_question_results)
        summary["chunk_count"] = len(chunks)

        print(json.dumps(summary, indent=2))

        misses = [r for r in per_question_results if not r["rank"]]
        if misses:
            print(f"\nMisses ({len(misses)}):")
            for miss in misses:
                print(f"  - {miss['question']}")
                print(f"    expected:  {miss['expected_sources']}")
                print(f"    retrieved: {miss['retrieved_sources']}")

        all_results[str(chunk_size)] = {
            "summary": summary,
            "results": per_question_results,
        }

        # Clean up so ablation runs never linger in the production vectorstore.
        client.delete_collection(name=collection_name)

    output_path = Path(__file__).resolve().parent / "chunk_size_ablation_results.json"
    output_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved full results to {output_path}")


if __name__ == "__main__":
    main()
