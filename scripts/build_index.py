from pathlib import Path
import json

import chromadb
from sentence_transformers import SentenceTransformer


# Project folder.
BASE_DIR = Path(__file__).resolve().parent.parent

# Chunks created by ingest_documents.py.
CHUNKS_FILE = BASE_DIR / "data" / "processed" / "chunks.json"

# Folder for the ChromaDB database.
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

# Name of the ChromaDB collection.
COLLECTION_NAME = "diasift_type2_diabetes"

# Embedding model used for searching by meaning.
EMBEDDING_MODEL_NAME = "multi-qa-mpnet-base-dot-v1"


def load_chunks() -> list[dict]:
    """Load the saved text chunks."""

    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {CHUNKS_FILE}. "
            "Run scripts/ingest_documents.py first."
        )

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    if len(chunks) == 0:
        raise ValueError("chunks.json is empty. Add documents and run ingestion again.")

    return chunks


def build_index() -> None:
    """
    1. Load the chunks.
    2. Turn each chunk into searchable numbers.
    3. Save the chunks and numbers in ChromaDB.
    """

    print("Loading chunks from chunks.json...")
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks.")

    print("Loading the embedding model...")

    # The model turns text into numbers that represent meaning.
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("Preparing ChromaDB...")

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    # Rebuild the collection so old chunks do not mix with new chunks.
    existing_collections = client.list_collections()

    existing_collection_names = [
        collection.name if hasattr(collection, "name") else collection
        for collection in existing_collections
    ]

    if COLLECTION_NAME in existing_collection_names:
        print(f"Deleting old collection: {COLLECTION_NAME}")
        client.delete_collection(name=COLLECTION_NAME)

    # "ip" matches this embedding model's scoring style.
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "ip"},
    )

    print("Preparing chunk text and metadata...")

    ids = []
    documents = []
    documents_for_embedding = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk["chunk_id"])

        documents.append(chunk["text"])

        # Add source details to help the embedding model.
        # The saved text still stays clean.
        documents_for_embedding.append(
            f"Source: {chunk['source']}\n"
            f"Document: {chunk['source_file']}\n\n"
            f"{chunk['text']}"
        )

        # Metadata helps show where an answer came from.
        metadatas.append(
            {
                "source": chunk["source"],
                "source_file": chunk["source_file"],
                "chunk_index": chunk["chunk_index"],
            }
        )

    print("Turning chunks into embeddings...")

    embeddings = model.encode(documents_for_embedding).tolist()

    print("Saving chunks and embeddings into ChromaDB...")

    # Save the text, source details, and embeddings.
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print("\nVector index created successfully.")
    print(f"Collection name: {COLLECTION_NAME}")
    print(f"Total chunks stored: {len(chunks)}")
    print(f"Saved in: {VECTORSTORE_DIR}")


if __name__ == "__main__":
    build_index()
