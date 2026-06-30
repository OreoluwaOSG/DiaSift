import re

from safety_filter import UNSAFE_QUESTION_REASON, is_unsafe_medical_question


# These are the three labels Diasift can show to the user.
STRONG_EVIDENCE = "Strong evidence"
PARTIAL_EVIDENCE = "Partial evidence"
NO_CLEAR_EVIDENCE = "No clear evidence"

# This reason is used when the search results are not good enough.
WEAK_RESULTS_REASON = "The retrieved chunks do not provide enough clear support."

# These common words do not help us judge whether a result is useful.
QUESTION_STOPWORDS = {
    "a",
    "about",
    "am",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "or",
    "should",
    "the",
    "to",
    "what",
    "when",
    "with",
}


def tokenize(text: str) -> set[str]:
    """Break text into useful words we can compare."""
    words = get_words(text)
    return {
        word
        for word in words
        if word not in QUESTION_STOPWORDS and len(word) > 1
    }


def get_words(text: str) -> set[str]:
    """Break text into all simple lowercase words."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def calculate_result_support(question: str, results: list[dict]) -> dict:
    """Measure how well the search results support the question."""
    if not results:
        # If there are no results, there is no evidence to use.
        return {
            "top_score": 0,
            "average_top_3_score": 0,
            "matched_term_ratio": 0,
            "supporting_result_count": 0,
        }

    # Turn the question into important words.
    question_terms = tokenize(question)

    # Only use the first few results because they should be the most relevant.
    top_results = results[:3]

    # The best result's score.
    top_score = results[0].get("relevance_score", 0)

    # The average score of the top 3 results.
    average_top_3_score = sum(
        result.get("relevance_score", 0) for result in top_results
    ) / len(top_results)

    # Check how many important question words appear in the top results.
    combined_text = " ".join(result.get("document", "") for result in top_results)
    result_terms = tokenize(combined_text)
    matched_terms = question_terms.intersection(result_terms)

    matched_term_ratio = len(matched_terms) / max(len(question_terms), 1)

    # Count how many results look useful enough to support an answer.
    supporting_result_count = sum(
        1 for result in results if result.get("relevance_score", 0) >= 0.75
    )

    return {
        "top_score": top_score,
        "average_top_3_score": average_top_3_score,
        "matched_term_ratio": matched_term_ratio,
        "supporting_result_count": supporting_result_count,
    }


def label_evidence_strength(question: str, results: list[dict]) -> dict:
    """
    Decide whether Diasift has enough evidence to answer.

    This is simple and rule based for now. Later, the backend and LLM can use
    this label to decide whether to answer, be cautious, or refuse.

    Important: safety checks live in safety_filter.py. That rule-based check is
    useful early on, but backend and LLM safety checks should still be added
    later.
    """
    # Safety comes first. Even if the search finds good text, Diasift should not
    # answer personal medical advice questions directly.
    if is_unsafe_medical_question(question):
        return {
            "label": NO_CLEAR_EVIDENCE,
            "reason": UNSAFE_QUESTION_REASON,
            "signals": calculate_result_support(question, results),
            "should_answer": False,
        }

    # Work out the basic evidence scores for the retrieved chunks.
    signals = calculate_result_support(question, results)

    # Strong evidence means the best results are clearly relevant and supported
    # by more than one chunk.
    if (
        signals["top_score"] >= 1.2
        and signals["average_top_3_score"] >= 0.7
        and signals["matched_term_ratio"] >= 0.5
        and signals["supporting_result_count"] >= 2
    ):
        return {
            "label": STRONG_EVIDENCE,
            "reason": "The top retrieved chunks look clearly relevant to the question.",
            "signals": signals,
            "should_answer": True,
        }

    # Partial evidence means something useful was found, but the support is not
    # strong enough to be fully confident.
    if (
        signals["top_score"] >= 0.75
        and signals["matched_term_ratio"] >= 0.5
        and signals["supporting_result_count"] >= 1
    ):
        return {
            "label": PARTIAL_EVIDENCE,
            "reason": "Some relevant information was found, but support is limited.",
            "signals": signals,
            "should_answer": True,
        }

    # If the results are weak or unclear, Diasift should not answer directly.
    return {
        "label": NO_CLEAR_EVIDENCE,
        "reason": WEAK_RESULTS_REASON,
        "signals": signals,
        "should_answer": False,
    }
