"""Map AI result into Avito form payload."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


DEFAULT_REQUIRED_FIELDS = {
    "category",
    "brand",
    "model",
    "price_rub",
    "city",
    "body_type",
    "drive_type",
    "color",
    "owners",
    "payment_per_month_rub",
}


@dataclass(frozen=True)
class AvitoMapResult:
    status: str
    mapped_avito: Optional[Dict]
    errors: List[str]


def _clean_text(text: str, *, max_length: int = 3000) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[\t\f\v]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned


def _validate_required_fields(
    avito_fields: Dict,
    required_fields: Iterable[str],
) -> List[str]:
    missing = [field for field in required_fields if not avito_fields.get(field)]
    if missing:
        return ["Missing required avito_fields: " + ", ".join(sorted(missing))]
    return []


def _prepare_photos(photo_files: List[str]) -> List[str]:
    ordered = [path for path in photo_files if path]
    return ordered


def map_to_avito(
    ai_result: Dict,
    photo_files: List[str],
    *,
    required_fields: Iterable[str] = DEFAULT_REQUIRED_FIELDS,
) -> AvitoMapResult:
    """Map ai_result to Avito payload with validation and text cleanup."""
    errors: List[str] = []

    title = ai_result.get("title")
    description = ai_result.get("description")
    avito_fields = ai_result.get("avito_fields") or {}

    if not isinstance(avito_fields, dict):
        return AvitoMapResult(
            status="NEED_ACTION",
            mapped_avito=None,
            errors=["avito_fields must be an object"],
        )

    if not title or not isinstance(title, str):
        errors.append("title is required")
    if not description or not isinstance(description, str):
        errors.append("description is required")

    errors.extend(_validate_required_fields(avito_fields, required_fields))

    photos = _prepare_photos(photo_files)
    if not photos:
        errors.append("At least one photo is required")

    if errors:
        return AvitoMapResult(status="NEED_ACTION", mapped_avito=None, errors=errors)

    mapped = {
        "title": _clean_text(title, max_length=100),
        "description": _clean_text(description),
        "photos": photos,
        **avito_fields,
    }

    return AvitoMapResult(status="READY_TO_POST", mapped_avito=mapped, errors=[])
