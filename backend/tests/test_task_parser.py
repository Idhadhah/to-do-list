import pytest
from unittest.mock import patch

from ai.task_parser import _extract_json, parse_task_description


def test_extract_json_handles_code_fence():
    raw = '```json\n{"title": "Buy milk", "due_date": null, "recurrence": "none"}\n```'
    result = _extract_json(raw)
    assert result == {"title": "Buy milk", "due_date": None, "recurrence": "none"}


def test_extract_json_handles_fence_without_json_label():
    raw = '```\n{"title": "Call mom", "due_date": null, "recurrence": "weekly"}\n```'
    result = _extract_json(raw)
    assert result["title"] == "Call mom"


def test_extract_json_handles_stray_prose_around_object():
    raw = 'Sure, here is the JSON: {"title": "Water plants", "due_date": null, "recurrence": "daily"} Hope that helps!'
    result = _extract_json(raw)
    assert result["title"] == "Water plants"


def test_extract_json_raises_on_completely_unusable_output():
    raw = "I'm sorry, I cannot help with that request."
    with pytest.raises(Exception):
        _extract_json(raw)


def test_parse_task_description_raises_value_error_on_garbage():
    with patch("ai.task_parser.generate_text", return_value="not json at all, sorry"):
        with pytest.raises(ValueError):
            parse_task_description("buy milk")