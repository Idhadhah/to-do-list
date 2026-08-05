import json
import re

from .gemini_client import generate_text

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    text = raw.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
    return json.loads(text)


def build_summary_prompt(tasks: list[dict], today: str) -> str:
    task_lines = "\n".join(
        f'- id={t["id"]}, text="{t["text"]}", due_date={t["due_date"] or "none"}, '
        f'recurrence={t["recurrence"]}, done={t["done"]}'
        for t in tasks
    )
    return f"""Today's date is {today} (UTC).

Here is a user's task list:
{task_lines}

Write a short natural-language summary of this list, and suggest a priority
order for tackling the not-done tasks.

Priority rules:
- Overdue tasks (due_date before today, not done) should rank first.
- Tasks due soonest should rank above tasks due later.
- Tasks with no due date rank after any tasks that have one.
- Done tasks should not appear in the priority order at all.

Respond with JSON ONLY — no markdown fences, no explanation. Use exactly
this shape:
{{"summary": "...", "priority_order": [task_id, task_id, ...]}}

"priority_order" must be a list of the "id" values above, not the text.
"""


def summarize_tasks(tasks: list[dict], today: str) -> dict:
    prompt = build_summary_prompt(tasks, today)
    raw = generate_text(prompt)
    try:
        data = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Could not parse Gemini response as JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Gemini response JSON was not an object.")
    return data