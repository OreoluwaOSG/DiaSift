# Diasift

Diasift is a web-based Type 2 Diabetes guideline assistant.

It uses Retrieval Augmented Generation (RAG) to search trusted public health guidance and return answers with citations. The project is for education only. It does not diagnose users, prescribe medicine, give personal treatment advice, or replace a healthcare professional.

## Project Aim

The aim of Diasift is to explore how RAG can make health information answers safer, clearer, and better supported by evidence.

## Main Features

- Searches Type 2 Diabetes guidance documents.
- Retrieves relevant evidence from trusted sources.
- Generates answers using the retrieved evidence.
- Shows citations for the sources used.
- Labels the evidence as `Strong evidence`, `Partial evidence`, or `No clear evidence`.
- Refuses unsafe, personal, or unsupported medical questions.

## Data Sources

Diasift uses public Type 2 Diabetes guidance from:

- NHS
- NICE
- WHO
- nidirect

The collected source files are stored in `data/raw/`.

## Project Structure

```text
diasift/
  backend/       FastAPI backend
  frontend/      Next.js web interface
  data/          Raw and processed source documents
  vectorstore/   ChromaDB vector database
  scripts/       Ingestion, indexing, retrieval, and RAG scripts
  evaluation/    Test questions and evaluation results
  docs/          Project notes
  README.md
```

## How It Works

1. Source documents are saved in `data/raw/`.
2. `scripts/ingest_documents.py` cleans the documents and splits them into chunks.
3. `scripts/build_index.py` creates a ChromaDB vector index from the chunks.
4. A user asks a question.
5. Diasift checks whether the question is in scope and safe to answer.
6. Diasift retrieves the most relevant chunks.
7. Diasift labels the strength of the evidence.
8. If the evidence is suitable, Diasift prepares an answer with citations.
9. If the question is unsafe or unsupported, Diasift refuses to answer directly.

## Setup

Create and activate a Python virtual environment:

```bash
python3 -m venv backend-venv
source backend-venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Install the frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

## Build the Knowledge Base

Run the ingestion script:

```bash
python scripts/ingest_documents.py
```

Build the vector index:

```bash
python scripts/build_index.py
```

These commands create the processed chunks and the ChromaDB index used by the RAG pipeline.

## Test the RAG Pipeline

Run a dry test without calling an external LLM API:

```bash
python scripts/rag_pipeline.py "What is type 2 diabetes?"
```

By default, this returns retrieved evidence and metadata without making a paid or external model call.

## Run the Backend

Start the FastAPI backend from the project root:

```bash
backend-venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open the API documentation at:

```text
http://127.0.0.1:8000/docs
```

Main endpoints:

- `GET /health`
- `POST /answer`

Example request:

```bash
curl -X POST http://127.0.0.1:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"question":"What is type 2 diabetes?","call_api":false}'
```

## Run the Frontend

In a second terminal, start the Next.js frontend:

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open the app at:

```text
http://127.0.0.1:3000
```

The frontend sends requests to the backend through:

- `GET /api/health`
- `POST /api/answer`

By default, the frontend expects the backend to run at `http://127.0.0.1:8000`.

## LLM API Setup

Diasift uses OpenAI by default and automatically retries with Gemini if the OpenAI call fails or returns an incomplete response. API keys are read only by the backend from the project-root `.env` file.

Create a local `.env` file with:

```dotenv
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
DIASIFT_OPENAI_MODEL=gpt-5.4-nano
DIASIFT_GEMINI_MODEL=gemini-2.5-flash
```

Do not prefix either key with `NEXT_PUBLIC_`, because API keys must never be exposed to the browser. Do not commit or submit `.env` files containing API keys.

You can also set the keys in your shell instead:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export GEMINI_API_KEY="your-api-key"
```

After adding or changing a key, restart the FastAPI backend. The frontend does not need an OpenAI key.

## Evaluation

The `evaluation/` folder contains test questions, retrieval evaluation scripts, abstention evaluation scripts, and saved result files.

Useful commands:

```bash
python evaluation/run_retrieval_eval.py
python evaluation/run_abstention_eval.py
```

## Safety Notice

Diasift is not a medical diagnosis tool. It gives general educational information only.

If a question asks for personal diagnosis, medication changes, dosage advice, or urgent medical help, Diasift should refuse to answer directly and recommend speaking to a qualified healthcare professional.

## Author

Oreoluwa Gabriel Sola-Ojo
