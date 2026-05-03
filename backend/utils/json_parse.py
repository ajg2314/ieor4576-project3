"""
JSON parsing utilities — ported from project 2 (pipeline/orchestrator.py).

Multi-layer approach:
  1. Strip markdown code fences
  2. Fix invalid escape sequences
  3. Extract last valid JSON object from mixed prose+JSON output
  4. json-repair as final fallback
"""
import json
import re

from json_repair import repair_json


def _sanitise_json(text: str) -> str:
    """Strip markdown fences and fix common LLM JSON escape errors."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()
    # \' is not valid JSON — apostrophes need no escaping
    text = text.replace("\\'", "'")
    # Remove invalid single-char escapes (valid: \" \\ \/ \b \f \n \r \t \uXXXX)
    text = re.sub(r"\\([^\"\\\/bfnrtu])", r"\1", text)
    return text


def _extract_json_object(text: str) -> str | None:
    """Find the last complete JSON object {...} in text (handles mixed prose+JSON)."""
    candidates = list(re.finditer(r"\{", text))
    for start_match in reversed(candidates):
        start = start_match.start()
        depth, in_string, escape = 0, False, False
        for i, ch in enumerate(text[start:]):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start: start + i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        break
    return None


def parse_llm_json(raw: str) -> dict:
    """Parse JSON from LLM output with multiple fallback layers."""
    if not raw or not raw.strip():
        return {}

    cleaned = _sanitise_json(raw)

    # Layer 1: direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Layer 2: extract last valid JSON object from mixed prose+JSON
    extracted = _extract_json_object(cleaned) or _extract_json_object(raw)
    if extracted:
        try:
            return json.loads(extracted)
        except Exception:
            pass

    # Layer 3: json-repair as final fallback
    result = repair_json(cleaned, return_objects=True)
    if isinstance(result, dict):
        return result

    raise ValueError(
        f"Could not parse LLM output as JSON.\nRaw (first 500 chars):\n{raw[:500]}"
    )
