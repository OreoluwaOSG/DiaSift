from argparse import ArgumentParser
import os
import sys

from llm_providers import DEFAULT_PROVIDER
from rag_pipeline import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    run_rag_pipeline,
)


def answer_question(
    question: str,
    call_api: bool = False,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> dict:
    """Run the shared RAG pipeline and return its result."""
    return run_rag_pipeline(
        question=question,
        call_api=call_api,
        provider=provider,
        model=model,
        max_output_tokens=max_output_tokens,
    )


def display_answer(answer_data: dict, show_prompts: bool = False) -> None:
    """Print the result in a simple way."""
    usage = answer_data["usage_estimate"]

    print("=" * 80)
    print(f"Question: {answer_data['question']}")
    print(f"Evidence strength: {answer_data['evidence_label']}")
    print(f"Evidence reason: {answer_data['evidence_reason']}")
    print(f"Unsafe question: {answer_data['unsafe_question']}")
    print(f"Provider: {answer_data['provider']}")
    print(f"Model: {answer_data['model']}")
    print(f"API called: {answer_data['api_called']}")
    print(
        "Estimated tokens: "
        f"input={usage['input_tokens']}, "
        f"max_output={usage['max_output_tokens']}"
    )
    print("Estimated max cost: check your provider's current free tier or pricing")
    print(f"Citations: {answer_data['citations']}")
    print(f"Retrieved sources: {answer_data['retrieved_sources']}")

    print("=" * 80)

    if answer_data["answer"] is None:
        print("\nDry run only. No LLM provider API call was made.")
        print("Use --call-api if you want to generate an LLM answer.")
    else:
        print("\nAnswer:")
        print(answer_data["answer"])

    if show_prompts:
        print("\n" + "=" * 80)
        print("System prompt")
        print("=" * 80)
        print(answer_data["system_prompt"])
        print("\n" + "=" * 80)
        print("User prompt")
        print("=" * 80)
        print(answer_data["user_prompt"])


def parse_args() -> ArgumentParser:
    """Set up command line options."""
    parser = ArgumentParser(description="Generate a Diasift RAG answer.")
    parser.add_argument("question", nargs="*", help="Question to ask Diasift.")
    parser.add_argument(
        "--call-api",
        action="store_true",
        help="Actually call the selected LLM provider. By default this script is dry-run only.",
    )
    parser.add_argument(
        "--show-prompts",
        action="store_true",
        help="Print the prompts that would be sent to the LLM.",
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
    return parser


def main() -> None:
    """Run the script from the command line."""
    parser = parse_args()
    args = parser.parse_args()

    if args.question:
        question = " ".join(args.question)
    else:
        question = input("Ask a Type 2 Diabetes question: ").strip()

    if not question:
        print("No question provided.")
        sys.exit(1)

    answer_data = answer_question(
        question=question,
        call_api=args.call_api,
        provider=args.provider,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
    )
    display_answer(answer_data, show_prompts=args.show_prompts)


if __name__ == "__main__":
    main()
