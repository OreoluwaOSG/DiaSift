import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_PROVIDER = "gemini"

# Gemini is the current default because it has a free tier.
# You can switch providers later without changing the RAG pipeline.
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-5.4-nano",
}

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def load_env_file(env_path: Path | None = None) -> None:
    """
    Load simple KEY=value lines from .env.

    This lets local scripts use GEMINI_API_KEY without printing or exposing it.
    """
    if env_path is None:
        env_path = Path(__file__).resolve().parent.parent / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def get_default_model(provider: str) -> str:
    """Get the default model for a provider."""
    return DEFAULT_MODELS.get(provider, "")


def extract_text_from_gemini_response(response_data: dict) -> str:
    """
    Pull answer text from a Gemini response.

    The exact response shape can vary, so this checks the common fields first
    and then looks for text blocks.
    """
    for key in ("output_text", "outputText", "text"):
        value = response_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    text_parts = []

    prompt_feedback = response_data.get("promptFeedback", {})
    block_reason = prompt_feedback.get("blockReason")
    if block_reason:
        raise RuntimeError(f"Gemini blocked the prompt. Reason: {block_reason}")

    candidates = response_data.get("candidates", [])
    for candidate in candidates:
        finish_reason = candidate.get("finishReason")
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        for part in parts:
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

        if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
            raise RuntimeError(f"Gemini did not return answer text. Finish reason: {finish_reason}")

    if text_parts:
        return "\n".join(text_parts)

    def collect_text(value):
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

            for child in value.values():
                collect_text(child)
        elif isinstance(value, list):
            for item in value:
                collect_text(item)

    collect_text(response_data)

    if text_parts:
        return "\n".join(text_parts)

    if candidates:
        finish_reasons = [
            candidate.get("finishReason", "unknown")
            for candidate in candidates
        ]
        raise RuntimeError(
            "Gemini returned a response, but no answer text was found. "
            f"Finish reasons: {finish_reasons}"
        )

    raise RuntimeError("Gemini returned a response with no candidates.")


def call_gemini_api(
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
) -> str:
    """Call Gemini using the API key in GEMINI_API_KEY."""
    load_env_file()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in your environment or .env file.")

    url = f"{GEMINI_API_BASE_URL}/models/{quote(model)}:generateContent?key={api_key}"

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "temperature": 0.2,
        },
    }

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API error {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Gemini API: {error.reason}") from error

    return extract_text_from_gemini_response(response_data)


def call_openai_api(
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
) -> str:
    """
    Call OpenAI if you choose to enable it later.

    This keeps OpenAI support separate from the main RAG flow.
    """
    load_env_file()

    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI Python package is not installed. "
            "Install it before using provider=openai."
        ) from error

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in your environment or .env file.")

    client = OpenAI()

    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=user_prompt,
        max_output_tokens=max_output_tokens,
    )

    return response.output_text


def call_llm(
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
) -> str:
    """Call the selected LLM provider."""
    if provider == "gemini":
        return call_gemini_api(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=max_output_tokens,
        )

    if provider == "openai":
        return call_openai_api(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=max_output_tokens,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
