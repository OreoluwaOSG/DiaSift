from pathlib import Path
import json


# Find the project's main folder from this script's location.
# This means the script still works even if it is run from another folder.
BASE_DIR = Path(__file__).resolve().parent.parent

# The input text files live here.
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# The finished JSON file will be placed in this folder.
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
OUTPUT_FILE = PROCESSED_DATA_DIR / "chunks.json"


def clean_text(text: str) -> str:
    """Remove blank lines and spaces from the start and end of each line."""
    # Turn one large block of text into a list of separate lines.
    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:
        # Remove unwanted spaces from both ends of this line.
        line = line.strip()

        # Keep the line only if something remains after cleaning it.
        if line:
            cleaned_lines.append(line)

    # Join the useful lines back together into one block of text.
    return "\n".join(cleaned_lines)


def split_text_into_chunks(
    text: str,
    chunk_size: int = 900,
    overlap: int = 150
) -> list[str]:
    """
    Cut a long piece of text into smaller, slightly overlapping pieces.

    ``chunk_size`` is the maximum number of characters in each piece.
    ``overlap`` is the number of characters repeated from the previous piece.
    Repeating some text gives later search or AI tools useful context when a
    sentence happens to be cut between two pieces.
    """
    chunks = []

    # "start" marks where the next piece begins in the full text.
    start = 0
    text_length = len(text)

    while start < text_length:
        # Take up to "chunk_size" characters from the current position.
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # Move forward, but keep "overlap" characters from the last piece.
        start += chunk_size - overlap

    return chunks


def create_source_name(file_path: Path) -> str:
    """
    Turn a file name into a more readable label for the JSON output.

    Example:
    nhs_type2_diabetes_treatment.txt
    becomes:
    Nhs Type2 Diabetes Treatment

    Python's title case does not know that "NHS" is an abbreviation, so it
    changes it to "Nhs" here.
    """
    name = file_path.stem.replace("_", " ")
    return name.title()


def ingest_documents() -> None:
    """
    Main function:
    1. Read every .txt file from data/raw.
    2. Clean its text.
    3. Cut the text into smaller pieces.
    4. Save every piece in data/processed/chunks.json.
    """
    # Create the output folder if it does not exist already.
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Make a list of every .txt file directly inside the raw-data folder.
    txt_files = list(RAW_DATA_DIR.glob("*.txt"))

    # Stop early and explain what is missing if there is nothing to process.
    if not txt_files:
        print(f"No .txt files found in {RAW_DATA_DIR}")
        print("Add your NHS/NICE text files to data/raw first.")
        return

    # This list will eventually contain pieces from every input file.
    all_chunks = []

    for file_path in txt_files:
        # Read one file, tidy its text, and divide it into smaller pieces.
        raw_text = file_path.read_text(encoding="utf-8")
        cleaned_text = clean_text(raw_text)
        chunks = split_text_into_chunks(cleaned_text)

        source_name = create_source_name(file_path)

        # Give each piece enough information to trace it back to its source.
        # Numbering starts at 1 because that is friendlier for people reading it.
        for index, chunk_text in enumerate(chunks, start=1):
            chunk_data = {
                # Example ID: nhs_diabetes_overview_001
                "chunk_id": f"{file_path.stem}_{index:03d}",
                "source": source_name,
                "source_file": file_path.name,
                "chunk_index": index,
                "text": chunk_text
            }

            all_chunks.append(chunk_data)

        print(f"Processed {file_path.name}: {len(chunks)} chunks")

    # Convert the Python list to readable JSON and save it as UTF-8 text.
    OUTPUT_FILE.write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nIngestion complete.")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Saved to: {OUTPUT_FILE}")


# Run the ingestion only when this file is launched directly.
# It will not run automatically if another Python file imports it.
if __name__ == "__main__":
    ingest_documents()
