"""Bounded theorem-proposal generation for CIO consultations."""

from __future__ import annotations

import json
from typing import Any

from .models import ConsultationKind
from .providers import Reasoner


class TheoremBuilderError(ValueError):
    """Theorem output was malformed or did not satisfy the proposal contract."""


def validate_theorem_output(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise TheoremBuilderError("Theorem Builder returned non-JSON output") from error
    if not isinstance(value, dict):
        raise TheoremBuilderError("Theorem Builder output must be an object")
    required = ("summary", "proposition", "supporting_patterns", "counterexamples",
                "limitations", "follow_up_questions")
    if any(not isinstance(value.get(key), str if key in {"summary", "proposition"} else list)
           for key in required):
        raise TheoremBuilderError("Theorem Builder output has an invalid schema")
    if not value["summary"].strip() or not value["proposition"].strip():
        raise TheoremBuilderError("Theorem Builder must provide a summary and proposition")
    if len(value["supporting_patterns"]) > 10 or len(value["counterexamples"]) > 10:
        raise TheoremBuilderError("Theorem Builder returned too many pattern entries")
    if len(value["limitations"]) > 10 or len(value["follow_up_questions"]) > 10:
        raise TheoremBuilderError("Theorem Builder returned too many follow-up entries")
    if any(not isinstance(item, str) or not item.strip()
           for key in required[2:] for item in value[key]):
        raise TheoremBuilderError("Theorem Builder lists must contain nonempty strings")
    return value


async def build_theorem(
    reasoner: Reasoner,
    *,
    brief: str,
    context: list[dict[str, object]],
) -> tuple[dict[str, Any], str]:
    prompt = json.dumps(
        {"brief": brief, "reviewed_case_context": context},
        ensure_ascii=True,
    )
    raw = await reasoner.respond(
        "theorem_builder",
        "Build scoped, testable propositions from reviewed evidence. Never treat an allegation as established. "
        "Return JSON with summary, proposition, supporting_patterns, counterexamples, limitations, "
        "and follow_up_questions; every list item must be a string.",
        prompt,
    )
    return validate_theorem_output(raw), raw
