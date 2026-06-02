"""Shared utilities for memory services."""

import json
import re


def parse_memory_json(text):
    """Parse JSON from LLM response, handling markdown code blocks.

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed dict or None if parsing fails.
    """
    if not text:
        return None

    # Try markdown code block
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try raw JSON
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try brace-delimited
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            pass

    return None
