"""AI client for generating structured listing data."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


REQUIRED_TOP_LEVEL_FIELDS = {"title", "description", "specs", "equipment", "avito_fields"}
REQUIRED_EQUIPMENT_SECTIONS = {
    "comfort",
    "interior",
    "security",
    "exterior",
    "assist",
    "visibility",
    "safety",
    "multimedia",
}
TRANSMISSION_ALLOWED = {"MT", "AT", "CVT", "AMT"}


@dataclass(frozen=True)
class AIClientResult:
    status: str
    ai_result: Optional[Dict]
    errors: List[str]


def _load_template(template_id: str, templates_dir: str) -> Dict:
    if importlib.util.find_spec("yaml") is None:
        raise RuntimeError(
            "PyYAML is required to load templates. Install with `pip install pyyaml`."
        )

    yaml = importlib.import_module("yaml")

    template_path = f"{templates_dir.rstrip('/')}/{template_id}.yaml"
    try:
        with open(template_path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:
        raise RuntimeError(f"Template not found: {template_path}") from exc


def _build_prompt(photo_paths: List[str], template: Dict) -> str:
    template_text = template.get("text_template", "")
    return (
        "Верни JSON строго по схеме. "
        "Не добавляй лишних ключей. "
        "Список фото: "
        f"{photo_paths}. "
        "Шаблон объявления: "
        f"{template_text}"
    )


def _parse_ai_response(response_text: str) -> Dict:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("AI response is not valid JSON") from exc


def _validate_ai_result(ai_result: Dict) -> List[str]:
    errors: List[str] = []

    missing = REQUIRED_TOP_LEVEL_FIELDS - set(ai_result.keys())
    if missing:
        errors.append(f"Missing top-level fields: {', '.join(sorted(missing))}")
        return errors

    specs = ai_result.get("specs", {})
    equipment = ai_result.get("equipment", {})
    avito_fields = ai_result.get("avito_fields", {})

    mileage = specs.get("mileage_km")
    if not isinstance(mileage, (int, float)):
        errors.append("specs.mileage_km must be a number")
    elif mileage > 160000:
        errors.append("specs.mileage_km must be <= 160000")

    payment = avito_fields.get("payment_per_month_rub")
    if not isinstance(payment, (int, float)):
        errors.append("avito_fields.payment_per_month_rub must be a number")
    elif not 5000 <= payment <= 25000:
        errors.append("avito_fields.payment_per_month_rub must be 5000..25000")

    equipment_keys = set(equipment.keys()) if isinstance(equipment, dict) else set()
    missing_sections = REQUIRED_EQUIPMENT_SECTIONS - equipment_keys
    if missing_sections:
        errors.append(
            "Missing equipment sections: "
            + ", ".join(sorted(missing_sections))
        )
    else:
        for section in REQUIRED_EQUIPMENT_SECTIONS:
            if not isinstance(equipment.get(section), list):
                errors.append(f"equipment.{section} must be an array")

    transmission = specs.get("transmission")
    if transmission not in TRANSMISSION_ALLOWED:
        errors.append("specs.transmission must be one of MT, AT, CVT, AMT")

    return errors


def generate_ai_result(
    photo_paths: List[str],
    template_id: str,
    *,
    templates_dir: str = "templates",
    responder: Optional[Callable[[str], str]] = None,
) -> AIClientResult:
    """Send photos + template to AI and return structured output.

    responder: a callable that takes a prompt and returns a JSON string.
    """
    template = _load_template(template_id, templates_dir)
    prompt = _build_prompt(photo_paths, template)

    if responder is None:
        raise RuntimeError("AI responder is not configured")

    try:
        response_text = responder(prompt)
        ai_result = _parse_ai_response(response_text)
    except (ValueError, RuntimeError) as exc:
        return AIClientResult(status="NEED_ACTION", ai_result=None, errors=[str(exc)])

    errors = _validate_ai_result(ai_result)
    if errors:
        return AIClientResult(status="NEED_ACTION", ai_result=ai_result, errors=errors)

    return AIClientResult(status="AI_READY", ai_result=ai_result, errors=[])
