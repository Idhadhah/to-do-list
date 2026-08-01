import os

from google import genai
from google.genai import errors as genai_errors


class GeminiClientError(Exception):
    """Raised whenever a Gemini API call can't be completed successfully."""


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiClientError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )
    return genai.Client(api_key=api_key)


def generate_text(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """
    Send a plain text prompt to Gemini and return its plain text response.

    Raises GeminiClientError on any failure (missing/invalid key, network
    issue, rate limit, timeout, empty response, etc.) instead of letting
    the raw SDK exception bubble up.
    """
    if not prompt or not prompt.strip():
        raise GeminiClientError("Prompt must not be empty.")

    client = _get_client()

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
    except genai_errors.APIError as e:
        raise GeminiClientError(f"Gemini API call failed: {e}") from e
    except Exception as e:
        raise GeminiClientError(f"Unexpected error calling Gemini: {e}") from e

    text = getattr(response, "text", None)
    if not text:
        raise GeminiClientError("Gemini returned an empty response.")

    return text