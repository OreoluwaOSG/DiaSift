from pathlib import Path
from functools import lru_cache
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
    "define",
    "does",
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
    "meaning",
    "mean",
    "means",
    "explain",
}


def normalize_question_text(text: str) -> str:
    """
    Normalize common user wording before search.

    This helps when users type things like type2, type-2, or T2D.
    """
    normalized = text.lower()
    normalized = re.sub(r"\btype\s*-?\s*1\b", "type 1", normalized)
    normalized = re.sub(r"\btype\s*-?\s*2\b", "type 2", normalized)
    normalized = re.sub(r"\btype1\b", "type 1", normalized)
    normalized = re.sub(r"\btype2\b", "type 2", normalized)
    normalized = re.sub(r"\bt1d\b", "type 1 diabetes", normalized)
    normalized = re.sub(r"\bt2d\b", "type 2 diabetes", normalized)
    normalized = re.sub(r"\bhba1c\b", "hba1c", normalized)
    return normalized


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the embedding model once per Python process."""
    try:
        return SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
    except Exception as error:
        raise RuntimeError(
            "The embedding model is not available locally. "
            "Run scripts/build_index.py once with internet access so the model "
            "can be downloaded, then start the backend again."
        ) from error


@lru_cache(maxsize=1)
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
    words = re.findall(r"[a-z0-9]+", normalize_question_text(text))
    return {word for word in words if word not in STOPWORDS}


def is_definition_question(question: str) -> bool:
    """Check if the question is asking for a definition."""
    question_lower = normalize_question_text(question).strip()
    return (
        question_lower.startswith("what is ")
        or "define" in question_lower
        or "meaning of" in question_lower
    )


def get_definition_target(question: str) -> dict:
    """Get the phrase being defined, such as glucose or type 2 diabetes."""
    question_lower = normalize_question_text(question).strip()

    patterns = [
        r"^what is (.+?)[\?\.]?$",
        r"^what are (.+?)[\?\.]?$",
        r"^define (.+?)[\?\.]?$",
        r"^explain (.+?)[\?\.]?$",
        r"^meaning of (.+?)[\?\.]?$",
        r"^what does (.+?) mean[\?\.]?$",
    ]

    for pattern in patterns:
        match = re.search(pattern, question_lower)
        if match:
            phrase = match.group(1).strip()
            terms = tokenize(phrase)
            ordered_terms = [
                word
                for word in re.findall(r"[a-z0-9]+", phrase)
                if word in terms
            ]

            return {
                "phrase": " ".join(ordered_terms),
                "terms": terms,
                "head_term": ordered_terms[-1] if ordered_terms else "",
            }

    terms = tokenize(question)
    ordered_terms = [
        word
        for word in re.findall(r"[a-z0-9]+", question_lower)
        if word in terms
    ]

    return {
        "phrase": " ".join(ordered_terms),
        "terms": terms,
        "head_term": ordered_terms[-1] if ordered_terms else "",
    }


def has_definition_phrase(text: str, phrase: str) -> bool:
    """Check for wording like 'glucose is' or 'type 2 diabetes means'."""
    if not phrase:
        return False

    escaped_phrase = re.escape(phrase)
    match = re.search(
        rf"\b{escaped_phrase}\b\s*(\([^)]+\))?\s+"
        r"(is|are|means|mean|refers to|happens when|is when)\b"
        r"\s*([a-z0-9]+)?",
        text,
    )

    if not match:
        return False

    next_word = match.group(3) or ""

    # These phrases mention a term but do not define it.
    non_definition_words = {
        "available",
        "eligible",
        "offered",
        "possible",
        "recommended",
        "used",
    }

    return next_word not in non_definition_words


def calculate_definition_score(document: str, definition_target: dict) -> float:
    """Score generic definition-style wording without hard-coding one topic."""
    definition_terms = definition_target["terms"]

    if not definition_terms:
        return 0

    document_lower = document.lower()
    first_section = document_lower[:500]
    phrase = definition_target["phrase"]
    head_term = definition_target["head_term"]
    definition_score = 0

    # Prefer exact definition wording near the top of a chunk.
    if has_definition_phrase(first_section, phrase):
        definition_score += 2.0
    elif has_definition_phrase(document_lower, phrase):
        definition_score += 1.2

    # If the phrase is "type 2 diabetes", a definition of "diabetes" can still
    # be useful because it defines the broader condition.
    if head_term and head_term != phrase:
        if has_definition_phrase(first_section, head_term):
            definition_score += 1.0
        elif has_definition_phrase(document_lower, head_term):
            definition_score += 0.5

    # Prefer chunks where the exact term appears near the start.
    if phrase and phrase in first_section:
        definition_score += 0.5

    # Prefer parenthetical definitions such as "glucose (sugar)".
    if head_term and re.search(rf"\b{re.escape(head_term)}\b\s*\([^)]+\)", document_lower):
        definition_score += 0.8

    # For definition questions, reduce chunks that are clearly about other
    # tasks, such as treatment or complications, rather than defining the term.
    first_line = document_lower.splitlines()[0] if document_lower.splitlines() else ""
    if first_line.startswith(
        (
            "treatment",
            "complications",
            "appointments",
            "medicine",
            "outcomes",
            "contact",
        )
    ):
        definition_score -= 0.6

    return definition_score


def rerank_results(question: str, results, number_of_results: int):
    """
    Sort search results again after Chroma returns them.
    This combines semantic search rank with simple word matching.
    """

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    ids = results["ids"][0]

    normalized_question = normalize_question_text(question)
    query_terms = tokenize(normalized_question)
    wants_definition = is_definition_question(normalized_question)
    definition_target = (
        get_definition_target(normalized_question) if wants_definition else None
    )

    ranked_results = []

    for index, document in enumerate(documents):
        document_lower = normalize_question_text(document)
        document_terms = tokenize(document)
        matching_terms = query_terms.intersection(document_terms)

        semantic_score = 1 / (index + 1)
        lexical_score = len(matching_terms) / max(len(query_terms), 1)
        intent_score = 0

        if wants_definition:
            intent_score += calculate_definition_score(document, definition_target)

        # Emergency chunks can be relevant for urgent questions, but they should
        # not dominate ordinary educational questions.
        if "call 999" in document_lower or "a&e" in document_lower:
            intent_score -= 0.3

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


def search_documents(question: str, number_of_results: int = 5, verbose: bool = True):
    """
    1. Turn the user's question into an embedding.
    2. Search ChromaDB for similar chunks.
    3. Rerank the results.
    """

    if verbose:
        print("Loading embedding model...")

    # Use the same model that built the index.
    model = get_embedding_model()

    if verbose:
        print("Loading ChromaDB collection...")
    collection = load_collection()

    if verbose:
        print("Turning question into an embedding...")

    # Turn the question into searchable numbers.
    normalized_question = normalize_question_text(question)
    question_embedding = model.encode([normalized_question]).tolist()

    if verbose:
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
