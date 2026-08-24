from pathlib import Path
import sys
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

DEFAULT_PROVIDER = "gemini"
DEFAULT_MAX_OUTPUT_TOKENS = 500


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    call_api: bool = False
    provider: Literal["gemini", "openai"] = DEFAULT_PROVIDER
    model: str | None = None
    max_output_tokens: int = Field(
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        ge=100,
        le=2000,
    )
    include_prompts: bool = False


class AnswerResponse(BaseModel):
    question: str
    answer: str | None
    evidence_label: str
    evidence_reason: str
    unsafe_question: bool
    scope_check: dict[str, Any]
    citations: list[str]
    retrieved_sources: list[str]
    retrieved_chunks: list[dict[str, Any]]
    provider: str
    model: str
    api_called: bool
    usage_estimate: dict[str, int]
    system_prompt: str | None = None
    user_prompt: str | None = None


class HealthResponse(BaseModel):
    status: str
    collection_name: str
    vectorstore_path: str
    indexed_chunks: int | None


app = FastAPI(
    title="Diasift API",
    description="FastAPI backend for the Diasift Type 2 Diabetes RAG pipeline.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "https://diasift.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Diasift API",
        "docs": "/docs",
        "health": "/health",
        "answer": "/answer",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    collection_name = "diasift_type2_diabetes"
    vectorstore_dir = BASE_DIR / "vectorstore"
    index_file = vectorstore_dir / "chroma.sqlite3"
    status = "ok" if index_file.exists() else "index_not_ready"

    return HealthResponse(
        status=status,
        collection_name=collection_name,
        vectorstore_path=str(vectorstore_dir),
        indexed_chunks=None,
    )


@app.post("/answer", response_model=AnswerResponse)
def answer(request: AnswerRequest) -> AnswerResponse:
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    try:
        from llm_providers import get_default_model
        from rag_pipeline import run_rag_pipeline

        model = request.model or get_default_model(request.provider)
        result = run_rag_pipeline(
            question=question,
            call_api=request.call_api,
            provider=request.provider,
            model=model,
            max_output_tokens=request.max_output_tokens,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    if not request.include_prompts:
        result.pop("system_prompt", None)
        result.pop("user_prompt", None)

    return AnswerResponse(**result)
