import re


# This reason is used when the question sounds too personal or unsafe.
# This is not a full safety system. It is an early warning step.
UNSAFE_QUESTION_REASON = (
    "The question appears to ask for personal medical advice, diagnosis, "
    "urgent care, or medication changes."
)

# Words that make a question sound personal instead of general.
PERSONAL_CONTEXT_TERMS = {
    "i",
    "im",
    "ive",
    "me",
    "my",
    "mine",
    "myself",
    "we",
    "our",
    "us",
    "wife",
    "husband",
    "partner",
    "child",
    "son",
    "daughter",
    "mum",
    "mom",
    "dad",
    "patient",
}

# Medical words that may mean the user wants advice about a real person.
PERSONAL_MEDICAL_TERMS = {
    "symptom",
    "symptoms",
    "blood",
    "sugar",
    "glucose",
    "hba1c",
    "diabetes",
    "diabetic",
    "prediabetes",
    "medicine",
    "medicines",
    "medication",
    "metformin",
    "insulin",
    "dose",
    "dosage",
    "diagnose",
    "diagnosis",
    "treatment",
    "treat",
    "pregnant",
    "pregnancy",
    "hypo",
    "hypoglycaemia",
    "hypoglycemia",
}

# Action words that often mean the user wants a decision, not education.
MEDICAL_ACTION_TERMS = {
    "start",
    "stop",
    "change",
    "increase",
    "decrease",
    "reduce",
    "take",
    "skip",
    "avoid",
    "diagnose",
    "treat",
}

# These patterns catch some clear personal medical advice questions.
# The wider word checks below catch more cases than this list alone.
PERSONAL_MEDICAL_PATTERNS = [
    r"\b(my|me|i|i'm|ive|i've)\b.*\b(symptoms?|blood sugar|glucose|hba1c|medication|medicine|metformin|insulin|dose|diagnos)",
    r"\bshould i\b",
    r"\bcan i stop\b",
    r"\bcan i take\b",
    r"\bwhat dose\b",
    r"\bdiagnose me\b",
    r"\bam i diabetic\b",
    r"\bdo i have diabetes\b",
]

# These patterns catch urgent or emergency-style medical questions.
URGENT_MEDICAL_PATTERNS = [
    r"\b(emergency|urgent|999|a&e|accident and emergency)\b",
    r"\b(chest pain|cannot breathe|can't breathe|unconscious|confusion|seizure)\b",
    r"\b(very high|extremely high|very low|hypo|hypoglycaemia|hypoglycemia)\b.*\b(blood sugar|glucose)\b",
]


def get_words(text: str) -> set[str]:
    """Break text into all simple lowercase words."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def has_personal_medical_context(question: str) -> bool:
    """Check if the question is about a real person's medical situation."""
    words = get_words(question)

    has_personal_words = bool(words.intersection(PERSONAL_CONTEXT_TERMS))
    has_medical_words = bool(words.intersection(PERSONAL_MEDICAL_TERMS))
    has_action_words = bool(words.intersection(MEDICAL_ACTION_TERMS))

    # Example: "I have symptoms" or "my blood sugar is high".
    if has_personal_words and has_medical_words:
        return True

    # Example: "Should I stop metformin?" or "Can my dad change insulin?"
    if has_personal_words and has_action_words:
        return True

    return False


def is_unsafe_medical_question(question: str) -> bool:
    """
    Check if the question should be avoided for safety reasons.

    This rule-based check will not catch every unsafe question. Backend and LLM
    safety checks should still be added later.
    """
    question_lower = question.lower()
    patterns = PERSONAL_MEDICAL_PATTERNS + URGENT_MEDICAL_PATTERNS

    # First catch very clear unsafe wording.
    if any(re.search(pattern, question_lower) for pattern in patterns):
        return True

    # Then catch broader personal medical wording.
    return has_personal_medical_context(question)
