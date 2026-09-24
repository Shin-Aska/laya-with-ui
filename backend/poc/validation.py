"""Bounded public request schema, independent of ML dependencies."""
import json
import re

MAX_BODY = 131_072
MAX_STATE = 24_000


class InvalidRequest(ValueError):
    pass


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InvalidRequest(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def parse_json(text):
    try:
        return json.loads(text, object_pairs_hook=_pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(InvalidRequest(f"Invalid number: {x}")))
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise InvalidRequest(f"Invalid JSON: {exc}") from exc


def _text(value, name, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise InvalidRequest(f"{name} must be nonempty text, at most {limit} characters.")


def _json_field(value, name, limit, allow_empty=False):
    if not isinstance(value, (str, dict, list)) and value is not None:
        raise InvalidRequest(f"{name} must be JSON text or an object.")
    if not allow_empty and (value is None or value == {} or value == [] or (isinstance(value, str) and not value.strip())):
        raise InvalidRequest(f"{name} cannot be empty.")
    try:
        size = len(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvalidRequest(f"{name} must be valid JSON: {exc}") from exc
    if size > limit:
        raise InvalidRequest(f"{name} exceeds {limit} characters.")


def validate(payload):
    if not isinstance(payload, dict) or set(payload) - {"state", "questions", "checkpoint"}:
        raise InvalidRequest("Use an object with state, questions and checkpoint only.")
    state = payload.get("state")
    if not isinstance(state, (str, dict, list)) or not state:
        raise InvalidRequest("State must be nonempty text, a JSON object, or a JSON array.")
    if isinstance(state, str) and not state.strip():
        raise InvalidRequest("State cannot be blank.")
    try:
        if len(json.dumps(state, ensure_ascii=False, allow_nan=False)) > MAX_STATE:
            raise InvalidRequest(f"State exceeds {MAX_STATE:,} characters. Use a short excerpt.")
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvalidRequest(str(exc)) from exc
    checkpoint = payload.get("checkpoint", "typed-decisions")
    if checkpoint not in ("english", "typed-decisions", "multilingual"):
        raise InvalidRequest("Unknown checkpoint.")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 8:
        raise InvalidRequest("Provide 1–8 questions.")
    for qid, q in questions.items():
        if not isinstance(qid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,47}", qid):
            raise InvalidRequest("Question IDs must start with a letter and use up to 48 letters, digits or underscores.")
        if not isinstance(q, dict) or set(q) - {"type", "instructions", "criteria"}:
            raise InvalidRequest(f"{qid}: use type, instructions and optional criteria only.")
        _json_field(q.get("instructions"), f"{qid}.instructions", 600)
        kind, criteria = q.get("type"), q.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 12:
                raise InvalidRequest(f"{qid}: choice requires 2–12 named criteria.")
            for key, description in criteria.items():
                _text(key, f"{qid} label", 64)
                _json_field(description, f"{qid}.{key}", 800, allow_empty=True)
        elif kind == "score":
            if not isinstance(criteria, list) or not 2 <= len(criteria) <= 7:
                raise InvalidRequest(f"{qid}: score requires 2–7 ordered descriptions.")
            for item in criteria:
                _json_field(item, f"{qid} score level", 800)
        elif kind == "noul":
            if criteria is not None:
                if not isinstance(criteria, dict) or set(criteria) != {"false", "true"}:
                    raise InvalidRequest(f"{qid}: noul criteria must contain false and true.")
                for item in criteria.values():
                    _json_field(item, f"{qid} boolean criterion", 800, allow_empty=True)
        else:
            raise InvalidRequest(f"{qid}: type must be choice, score or noul.")
    return {"state": state, "questions": questions, "checkpoint": checkpoint}
