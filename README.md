# Diasift

Diasift is a web based Type 2 Diabetes guideline assistant. It uses Retrieval Augmented Generation to search trusted medical guidance documents and provide evidence based answers with citations.

The project focuses on Type 2 Diabetes guidance from public sources such as NHS and NICE. It is designed for educational use only and does not diagnose users, prescribe medication, or replace healthcare professionals.

## Project Aim

The aim of Diasift is to investigate how Retrieval Augmented Generation can be used to provide safer and more grounded answers to Type 2 Diabetes guideline questions.

## Main Features

- Search Type 2 Diabetes guidance documents
- Retrieve relevant evidence from trusted sources
- Generate answers using retrieved documents
- Show citations for answers
- Label evidence strength as:
  - Strong evidence
  - Partial evidence
  - No clear evidence
- Refuse unsafe or unsupported medical questions

## Project Structure

```text
diasift/
  backend/
  frontend/
  data/
    raw/
    processed/
  vectorstore/
  scripts/
  evaluation/
  docs/
  README.md

## Folder Explanation

- `backend/` contains the FastAPI backend.
- `frontend/` contains the web interface.
- `data/raw/` contains the original Type 2 Diabetes source documents.
- `data/processed/` contains cleaned and chunked document data.
- `vectorstore/` contains the ChromaDB vector database files.
- `scripts/` contains Python scripts for processing, indexing and testing.
- `evaluation/` contains test questions and evaluation results.
- `docs/` contains project notes, source records and design decisions.


Completed so far:

- Project folder structure created
- Initial Type 2 Diabetes documents collected
- Document ingestion script created
- Documents can be cleaned and split into chunks

Next stage:

- Build a vector index using ChromaDB
- Test semantic search on the document chunks

## How to Run the Current Script

Make sure you are inside the project folder:

```bash
cd diasift

Run the document ingestion script:

python3 scripts/ingest_documents.py

This reads .txt files from:

data/raw/

and creates:

data/processed/chunks.json
Data Sources

The project will use trusted public Type 2 Diabetes guidance sources such as:

NHS
NICE
Diabetes UK, if suitable

All sources will be recorded in:

docs/data_sources.md
Safety Notice

Diasift is not a medical diagnosis tool. It does not provide personal medical advice, medication instructions or emergency support.

If a user asks a personal or unsafe medical question, the system should refuse to answer directly and recommend speaking to a qualified healthcare professional.

Planned Development Roadmap
Document ingestion
Vector index creation
Search testing
Evidence strength labelling
Unsafe question detection
Prompt engineering
LLM answer generation
FastAPI backend
Frontend interface
Evaluation with test questions
Final project polish
Author

Oreoluwa Gabriel Sola-Ojo