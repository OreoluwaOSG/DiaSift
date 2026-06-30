from argparse import ArgumentParser
import json
import os
import sys

from evidence_label import NO_CLEAR_EVIDENCE, label_evidence_strength
from llm_providers import DEFAULT_PROVIDER, call_llm, get_default_model
from prompts import build_system_prompt, build_user_prompt, get_chunk_source, get_chunk_text
from safety_filter import is_unsafe_medical_question
from search_test import search_documents


DEFAULT_MAX_OUTPUT_TOKENS = 500


def estimate_tokens(text: str) -> int:
    """
    Rough token estimate.

    This is not exact, but it helps show how much text may be sent to the LLM.
    """
    return max(1, len(text) // 4)


def estimate_usage(
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
) -> dict:
    """Estimate the input and output token limits."""
    return {
        "input_tokens": estimate_tokens(system_prompt) + estimate_tokens(user_prompt),
        "max_output_tokens": max_output_tokens,
    }


def build_local_answer(question: str, evidence_label: str, unsafe_question: bool) -> str | None:
    """
    Return a local answer when an LLM call is not needed.

    This saves Gemini usage for unsafe questions and unsupported questions.
    """
    if unsafe_question:
        return (
            "Diasift cannot advise you to stop, start, or change medication. "
            "Diasift also cannot provide diagnosis, dosage advice, or personal "
            "treatment decisions. Please speak to a GP, diabetes nurse, "
            "pharmacist, or other qualified healthcare professional."
        )

    if evidence_label == NO_CLEAR_EVIDENCE:
        return (
            "There is not enough clear evidence in the provided sources to answer "
            f"this question: {question}"
        )

    return None


def format_retrieved_chunks(results: list[dict]) -> list[dict]:
    """
    Return retrieved chunks in a clean backend-friendly shape.

    The search script uses document/metadata. The backend can use this simpler
    source/text shape later.
    """
    formatted_chunks = []

    for result in results:
        metadata = result.get("metadata", {})

        formatted_chunks.append(
            {
                "source": get_chunk_source(result),
                "source_file": metadata.get("source_file"),
                "chunk_index": metadata.get("chunk_index"),
                "text": get_chunk_text(result),
                "relevance_score": result.get("relevance_score"),
            }
        )

    return formatted_chunks


def get_unique_sources(chunks: list[dict]) -> list[str]:
    """Return source names once, in the order they first appear."""
    sources = []

    for chunk in chunks:
        source = chunk.get("source")

        if source and source not in sources:
            sources.append(source)

    return sources


def run_rag_pipeline(
    question: str,
    call_api: bool = False,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> dict:
    """
    Run Diasift's full RAG pipeline.

    1. Check if the question is unsafe.
    2. Search trusted Type 2 Diabetes chunks.
    3. Label the evidence strength.
    4. Build the LLM prompt.
    5. Optionally call the selected LLM.
    6. Return answer, citations, evidence label, and retrieved sources.
    """
    if model is None:
        model = get_default_model(provider)

    unsafe_question = is_unsafe_medical_question(question)

    # Unsafe questions do not need retrieval or an LLM call.
    if unsafe_question:
        evidence_label = NO_CLEAR_EVIDENCE
        answer = build_local_answer(question, evidence_label, unsafe_question)

        return {
            "question": question,
            "answer": answer,
            "evidence_label": evidence_label,
            "evidence_reason": "The question appears to ask for personal medical advice, diagnosis, urgent care, or medication changes.",
            "unsafe_question": True,
            "citations": [],
            "retrieved_sources": [],
            "retrieved_chunks": [],
            "provider": provider,
            "model": model,
            "api_called": False,
            "usage_estimate": {
                "input_tokens": 0,
                "max_output_tokens": 0,
            },
        }

    results = search_documents(question)
    evidence = label_evidence_strength(question, results)
    evidence_label = evidence["label"]
    retrieved_chunks = format_retrieved_chunks(results)
    retrieved_sources = get_unique_sources(retrieved_chunks)

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        question=question,
        evidence_label=evidence_label,
        retrieved_chunks=retrieved_chunks,
        unsafe_question=False,
    )
    usage_estimate = estimate_usage(system_prompt, user_prompt, max_output_tokens)

    local_answer = build_local_answer(question, evidence_label, unsafe_question)

    if local_answer is not None:
        return {
            "question": question,
            "answer": local_answer,
            "evidence_label": evidence_label,
            "evidence_reason": evidence["reason"],
            "unsafe_question": False,
            "citations": [],
            "retrieved_sources": retrieved_sources,
            "retrieved_chunks": retrieved_chunks,
            "provider": provider,
            "model": model,
            "api_called": False,
            "usage_estimate": usage_estimate,
        }

    if call_api:
        answer = call_llm(
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=max_output_tokens,
        )

        if not answer.strip():
            raise RuntimeError(
                "The LLM provider returned an empty answer. Try increasing "
                "--max-output-tokens or inspect the generated prompts."
            )

        api_called = True
    else:
        answer = None
        api_called = False

    return {
        "question": question,
        "answer": answer,
        "evidence_label": evidence_label,
        "evidence_reason": evidence["reason"],
        "unsafe_question": False,
        "citations": retrieved_sources,
        "retrieved_sources": retrieved_sources,
        "retrieved_chunks": retrieved_chunks,
        "provider": provider,
        "model": model,
        "api_called": api_called,
        "usage_estimate": usage_estimate,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


def display_pipeline_result(result: dict, show_prompts: bool = False) -> None:
    """Print the pipeline result as readable JSON."""
    output = {
        key: value
        for key, value in result.items()
        if show_prompts or key not in ("system_prompt", "user_prompt")
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


def parse_args() -> ArgumentParser:
    """Set up command line options."""
    parser = ArgumentParser(description="Run the full Diasift RAG pipeline.")
    parser.add_argument("question", nargs="*", help="Question to ask Diasift.")
    parser.add_argument(
        "--call-api",
        action="store_true",
        help="Actually call the selected LLM provider. By default this is dry-run only.",
    )
    parser.add_argument(
        "--provider",
        default=os.getenv("DIASIFT_LLM_PROVIDER", DEFAULT_PROVIDER),
        choices=["gemini", "openai"],
        help=f"LLM provider to use. Default: {DEFAULT_PROVIDER}",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DIASIFT_LLM_MODEL"),
        help="Model to use. If omitted, Diasift picks the provider default.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help=f"Maximum answer length. Default: {DEFAULT_MAX_OUTPUT_TOKENS}",
    )
    parser.add_argument(
        "--show-prompts",
        action="store_true",
        help="Include system_prompt and user_prompt in the JSON output.",
    )
    return parser


def main() -> None:
    """Run the pipeline from the command line."""
    parser = parse_args()
    args = parser.parse_args()

    if args.question:
        question = " ".join(args.question)
    else:
        question = input("Ask a Type 2 Diabetes question: ").strip()

    if not question:
        print("No question provided.")
        sys.exit(1)

    result = run_rag_pipeline(
        question=question,
        call_api=args.call_api,
        provider=args.provider,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
    )
    display_pipeline_result(result, show_prompts=args.show_prompts)


if __name__ == "__main__":
    main()
