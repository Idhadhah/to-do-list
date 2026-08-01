import json
import re
from datetime import datetime, timezone

from .gemini_client import generate_text

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    text = raw.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    else:
        # fallback: grab the first {...} block in case Gemini added prose
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
    return json.loads(text)


def build_prompt(description: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""Today's date is {today} (UTC).

Convert the task description into JSON. Respond with JSON ONLY — no markdown
fences, no explanation.

Use exactly this shape:
{{"title": "...", "due_date": "YYYY-MM-DDTHH:MM:SS or null", "recurrence": "none|daily|weekly|monthly"}}

Rules:
- "title": short clean summary, no date/time phrases in it.
- "due_date": ISO-8601 datetime, or null if no date/time is mentioned.
- "recurrence": exactly one of none, daily, weekly, monthly.

Task description: "{description}"
"""


def parse_task_description(description: str) -> dict:
    """
    Raises GeminiClientError on API failure, ValueError if the response
    can't be parsed as usable JSON. Caller maps these to HTTP responses.
    """
    raw = generate_text(build_prompt(description))
    try:
        data = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Could not parse Gemini response as JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Gemini response JSON was not an object.")
    return data