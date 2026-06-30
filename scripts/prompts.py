def build_system_prompt() -> str:
    """
    Build the main rules for the LLM.

    The system prompt is the rulebook Diasift should follow every time.
    """

    return """
You are Diasift, a Type 2 Diabetes guideline assistant.

Your role is to answer general educational questions using only the provided Type 2 Diabetes guidance sources.

Important rules:
1. Use only the provided context.
2. Do not diagnose users.
3. Do not prescribe medication.
4. Do not recommend medication doses.
5. Do not tell users to start, stop, or change medication.
6. Do not replace a doctor, nurse, pharmacist, or diabetes specialist.
7. If the provided context does not contain enough information, say that there is not enough evidence in the provided sources.
8. If the question is unsafe or asks for personal medical advice, give a safe refusal.
9. Keep answers clear and simple.
10. Include citations using the source names provided.
""".strip()


def get_chunk_source(chunk: dict) -> str:
    """Get the source name from a retrieved chunk."""
    metadata = chunk.get("metadata", {})
    return chunk.get("source") or metadata.get("source") or "Unknown source"


def get_chunk_text(chunk: dict) -> str:
    """Get the text from a retrieved chunk."""
    return chunk.get("text") or chunk.get("document") or ""


def build_context_text(retrieved_chunks: list[dict]) -> str:
    """Turn retrieved chunks into context the LLM can read."""
    context_parts = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        source = get_chunk_source(chunk)
        text = get_chunk_text(chunk)

        context_parts.append(f"[Source {index}: {source}]\n{text}")

    return "\n\n".join(context_parts)


def build_user_prompt(
    question: str,
    evidence_label: str,
    retrieved_chunks: list[dict],
    unsafe_question: bool = False,
) -> str:
    """
    Build the user prompt for the LLM.

    This gives the LLM the question, evidence label, retrieved chunks, and
    safety status. The LLM should answer using only this information.
    """

    if unsafe_question:
        return f"""
The user asked this question:
{question}

This question has been marked as unsafe or personal medical advice.

Write a short safe response.
Do not answer the medical question directly.
Tell the user that Diasift cannot provide diagnosis, medication advice, dosage advice, or personal treatment decisions.
Suggest speaking to a qualified healthcare professional.
""".strip()

    context_text = build_context_text(retrieved_chunks)

    return f"""
The user asked this question:
{question}

Evidence strength label:
{evidence_label}

Retrieved context:
{context_text}

Write an answer using only the retrieved context.

Instructions:
- If the evidence label is "Strong evidence", answer clearly using the sources.
- If the evidence label is "Partial evidence", answer carefully and say that the available sources only partly answer the question.
- If the evidence label is "No clear evidence", say there is not enough evidence in the provided sources.
- Do not add medical information that is not in the retrieved context.
- Do not diagnose or give personal treatment advice.
- Include citations using the source names.
""".strip()
