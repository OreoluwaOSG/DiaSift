from pathlib import Path
import sys
import re

import chromadb
from sentence_transformers import SentenceTransformer

from evidence_label import label_evidence_strength


# Project folder.
BASE_DIR = Path(__file__).resolve().parent.parent

# Folder where ChromaDB saved the index.
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

# Must match build_index.py.
COLLECTION_NAME = "diasift_type2_diabetes"
EMBEDDING_MODEL_NAME = "multi-qa-mpnet-base-dot-v1"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "how",
    "in",
    "is",
    "it",
    "of",
    "or",
    "the",
    "to",
    "what",
}


def load_collection():
    """Load the ChromaDB collection."""

    if not VECTORSTORE_DIR.exists():
        raise FileNotFoundError(
            "The vectorstore folder does not exist yet. "
            "Run scripts/build_index.py first."
        )

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        raise ValueError(
            f"Could not find the collection '{COLLECTION_NAME}'. "
            "Run scripts/build_index.py first."
        )

    return collection


def tokenize(text: str) -> set[str]:
    """Get the useful words from some text."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word for word in words if word not in STOPWORDS}


def is_definition_question(question: str) -> bool:
    """Check if the question is asking for a definition."""
    question_lower = question.lower().strip()
    return (
        question_lower.startswith("what is ")
        or "define" in question_lower
        or "meaning of" in question_lower
    )


def rerank_results(question: str, results, number_of_results: int):
    """
    Sort search results again after Chroma returns them.
    This helps definition questions prefer overview chunks.
    """

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    ids = results["ids"][0]

    query_terms = tokenize(question)
    wants_definition = is_definition_question(question)

    ranked_results = []

    for index, document in enumerate(documents):
        document_lower = document.lower()
        document_terms = tokenize(document)
        matching_terms = query_terms.intersection(document_terms)

        semantic_score = 1 / (index + 1)
        lexical_score = len(matching_terms) / max(len(query_terms), 1)
        intent_score = 0

        if wants_definition:
            source_file = metadatas[index].get("source_file", "").lower()
            first_line = document_lower.splitlines()[0]

            if "diabetes is a condition" in document_lower:
                intent_score += 2.5
            elif "diabetes is" in document_lower:
                intent_score += 1.5

            if source_file == "nhs_diabetes_overview.txt":
                intent_score += 0.8

            if "causes of diabetes" in document_lower:
                intent_score += 0.5

            if first_line.startswith(("complications", "treatment", "medicine")):
                intent_score -= 1.0
            if any(topic in source_file for topic in ("complications", "treatment")):
                intent_score -= 0.8
            if "path to remission programme" in first_line:
                intent_score -= 1.0
            if "path_to_remission" in source_file:
                intent_score -= 0.8
            if "call 999" in document_lower or "a&e" in document_lower:
                intent_score -= 1.0

        relevance_score = semantic_score + lexical_score + intent_score

        ranked_results.append(
            {
                "id": ids[index],
                "document": document,
                "metadata": metadatas[index],
                "distance": distances[index],
                "relevance_score": relevance_score,
            }
        )

    ranked_results.sort(key=lambda item: item["relevance_score"], reverse=True)
    return ranked_results[:number_of_results]


def search_documents(question: str, number_of_results: int = 5):
    """
    1. Turn the user's question into an embedding.
    2. Search ChromaDB for similar chunks.
    3. Rerank the results.
    """

    print("Loading embedding model...")

    # Use the same model that built the index.
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("Loading ChromaDB collection...")
    collection = load_collection()

    print("Turning question into an embedding...")

    # Turn the question into searchable numbers.
    question_embedding = model.encode([question]).tolist()

    print("Searching for relevant chunks...\n")

    candidate_count = min(max(number_of_results * 3, 10), collection.count())

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    return rerank_results(question, results, number_of_results)


def display_results(question: str, results):
    """Print the search results."""
    evidence = label_evidence_strength(question, results)
    signals = evidence["signals"]

    print("=" * 80)
    print(f"Question: {question}")
    print(f"Evidence strength: {evidence['label']}")
    print(f"Evidence reason: {evidence['reason']}")
    print(f"Should answer directly: {evidence['should_answer']}")
    print(
        "Evidence signals: "
        f"top_score={signals['top_score']:.3f}, "
        f"average_top_3_score={signals['average_top_3_score']:.3f}, "
        f"matched_term_ratio={signals['matched_term_ratio']:.3f}, "
        f"supporting_result_count={signals['supporting_result_count']}"
    )
    print("=" * 80)

    if not results:
        print("No matching chunks found.")
        return

    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]
        document = result["document"]

        print(f"\nResult {index}")
        print("-" * 80)
        print(f"Source: {metadata.get('source')}")
        print(f"Source file: {metadata.get('source_file')}")
        print(f"Chunk index: {metadata.get('chunk_index')}")
        print(f"Vector distance score: {result['distance']}")
        print(f"Reranked relevance score: {result['relevance_score']:.3f}")

        print("\nText preview:")
        print(document[:700])

        if len(document) > 700:
            print("...")


def main():
    """
    Run a search test.

    You can use it in two ways:

    1. With a question directly:
       python3 scripts/search_test.py "What is type 2 diabetes?"

    2. Without a question:
       python3 scripts/search_test.py
       Then type the question when asked.
    """

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Ask a Type 2 Diabetes question: ").strip()

    if not question:
        print("No question provided.")
        return

    results = search_documents(question)
    display_results(question, results)


if __name__ == "__main__":
    main()
