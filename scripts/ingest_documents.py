from pathlib import Path
import json


# Project folder.
BASE_DIR = Path(__file__).resolve().parent.parent

# Original text files.
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Cleaned chunks will be saved here.
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
OUTPUT_FILE = PROCESSED_DATA_DIR / "chunks.json"


def clean_text(text: str) -> str:
    """Remove empty lines and extra spaces."""
    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def split_text_into_chunks(
    text: str,
    chunk_size: int = 900,
    overlap_paragraphs: int = 1,
) -> list[str]:
    """
    Split text into smaller chunks.
    Paragraphs are kept together when possible.
    """

    paragraphs = text.split("\n")

    chunks = []
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        paragraph_length = len(paragraph)

        if current_length + paragraph_length > chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))

            # Repeat the last paragraph in the next chunk for context.
            current_chunk = current_chunk[-overlap_paragraphs:]
            current_length = sum(len(p) for p in current_chunk)

        current_chunk.append(paragraph)
        current_length += paragraph_length

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def create_source_name(file_path: Path) -> str:
    """
    Turn a file name into a readable source name.

    Example:
    nhs_type2_diabetes_treatment.txt
    becomes:
    Nhs Type2 Diabetes Treatment
    """
    name = file_path.stem.replace("_", " ")
    return name.title()


def ingest_documents() -> None:
    """
    1. Read every .txt file from data/raw.
    2. Clean its text.
    3. Split it into chunks.
    4. Save the chunks to chunks.json.
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    txt_files = list(RAW_DATA_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {RAW_DATA_DIR}")
        print("Add your NHS/NICE text files to data/raw first.")
        return

    all_chunks = []

    for file_path in txt_files:
        raw_text = file_path.read_text(encoding="utf-8")
        cleaned_text = clean_text(raw_text)
        chunks = split_text_into_chunks(cleaned_text)

        source_name = create_source_name(file_path)

        for index, chunk_text in enumerate(chunks, start=1):
            chunk_data = {
                "chunk_id": f"{file_path.stem}_{index:03d}",
                "source": source_name,
                "source_file": file_path.name,
                "chunk_index": index,
                "text": chunk_text,
            }

            all_chunks.append(chunk_data)

        print(f"Processed {file_path.name}: {len(chunks)} chunks")

    OUTPUT_FILE.write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\nIngestion complete.")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Saved to: {OUTPUT_FILE}")


# Run this file only when called directly.
if __name__ == "__main__":
    ingest_documents()
