import re


SCOPE_REFUSAL = (
    "Diasift can only answer general educational questions about Type 2 "
    "Diabetes, diabetes care, symptoms, diet, remission, medication, lifestyle, "
    "and closely related health information. There is not enough relevant "
    "evidence in the provided sources to answer this question."
)

# These terms describe the area Diasift is meant to cover.
IN_SCOPE_TERMS = {
    "a1c",
    "blood",
    "bmi",
    "cardiovascular",
    "complications",
    "diabetes",
    "diabetic",
    "diet",
    "exercise",
    "glucose",
    "glycaemia",
    "glycemia",
    "hba1c",
    "health",
    "hypo",
    "hypoglycaemia",
    "hypoglycemia",
    "insulin",
    "lifestyle",
    "medicine",
    "medicines",
    "medication",
    "metformin",
    "obesity",
    "overweight",
    "prediabetes",
    "pregnancy",
    "remission",
    "risk",
    "sugar",
    "symptom",
    "symptoms",
    "treatment",
    "weight",
}

# These terms often mean the question is outside a medical guidance assistant.
OUT_OF_SCOPE_TERMS = {
    "bank",
    "benefit",
    "benefits",
    "car",
    "claim",
    "claims",
    "contract",
    "credit",
    "employment",
    "finance",
    "financial",
    "insurance",
    "insurer",
    "job",
    "legal",
    "loan",
    "mortgage",
    "salary",
    "tax",
    "university",
    "visa",
}


def get_words(text: str) -> set[str]:
    """Break text into simple lowercase words."""
    normalized = text.lower()
    normalized = re.sub(r"\btype\s*-?\s*1\b", "type 1", normalized)
    normalized = re.sub(r"\btype\s*-?\s*2\b", "type 2", normalized)
    normalized = re.sub(r"\btype1\b", "type 1", normalized)
    normalized = re.sub(r"\btype2\b", "type 2", normalized)
    normalized = re.sub(r"\bt1d\b", "type 1 diabetes", normalized)
    normalized = re.sub(r"\bt2d\b", "type 2 diabetes", normalized)
    return set(re.findall(r"[a-z0-9]+", normalized))


def get_retrieved_text(retrieved_chunks: list[dict]) -> str:
    """Join retrieved chunk text so it can be checked for scope."""
    texts = []

    for chunk in retrieved_chunks[:3]:
        texts.append(chunk.get("text") or chunk.get("document") or "")

    return " ".join(texts)


def check_question_scope(
    question: str,
    retrieved_chunks: list[dict],
    evidence: dict,
) -> dict:
    """
    Decide whether the question belongs in Diasift's Type 2 Diabetes scope.

    This is still rule based, but it does not rely only on the user's wording.
    It also checks whether the retrieved chunks and evidence signals support the
    question.
    """
    question_words = get_words(question)
    retrieved_words = get_words(get_retrieved_text(retrieved_chunks))

    matched_scope_terms = sorted(question_words.intersection(IN_SCOPE_TERMS))
    matched_out_of_scope_terms = sorted(question_words.intersection(OUT_OF_SCOPE_TERMS))

    signals = evidence.get("signals", {})
    matched_term_ratio = signals.get("matched_term_ratio", 0)
    supporting_result_count = signals.get("supporting_result_count", 0)

    if matched_out_of_scope_terms:
        return {
            "in_scope": False,
            "reason": (
                "The question appears to include non-medical or administrative "
                f"topics: {', '.join(matched_out_of_scope_terms)}."
            ),
            "matched_scope_terms": matched_scope_terms,
            "matched_out_of_scope_terms": matched_out_of_scope_terms,
        }

    if matched_scope_terms:
        return {
            "in_scope": True,
            "reason": "The question contains terms that fit Diasift's Type 2 Diabetes scope.",
            "matched_scope_terms": matched_scope_terms,
            "matched_out_of_scope_terms": [],
        }

    # Some valid questions use broader wording, so allow them if the retrieved
    # evidence strongly links the question to the diabetes source material.
    retrieved_scope_terms = question_words.intersection(retrieved_words).intersection(
        IN_SCOPE_TERMS
    )

    if retrieved_scope_terms and matched_term_ratio >= 0.5 and supporting_result_count >= 1:
        return {
            "in_scope": True,
            "reason": "The retrieved chunks connect the question to Diasift's diabetes scope.",
            "matched_scope_terms": sorted(retrieved_scope_terms),
            "matched_out_of_scope_terms": [],
        }

    return {
        "in_scope": False,
        "reason": "The question does not clearly fit Diasift's Type 2 Diabetes scope.",
        "matched_scope_terms": [],
        "matched_out_of_scope_terms": [],
    }
