"""Poster for filling and publishing Avito listings in a running profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class AvitoPostResult:
    status: str
    post_url: Optional[str]
    errors: List[str]
    step_log: List[str]
    screenshot_path: Optional[str]


def post_listing(
    mapped_avito: Dict,
    photo_files: List[str],
    *,
    form_filler: Callable[[Dict, List[str], Callable[[str], None]], Dict],
    screenshotter: Optional[Callable[[str], str]] = None,
) -> AvitoPostResult:
    """Fill and publish an Avito listing in an active Dolphin profile.

    form_filler: callable that performs UI automation and returns a dict with keys:
      - status: "posted" | "need_action" | "failed"
      - post_url: optional URL when posted
      - error: optional error message
    screenshotter: callable that accepts a reason and returns screenshot path.
    """
    step_log: List[str] = []

    def log_step(message: str) -> None:
        step_log.append(message)

    try:
        log_step("Starting Avito form fill")
        result = form_filler(mapped_avito, photo_files, log_step)
        status = result.get("status")
        post_url = result.get("post_url")
        error_message = result.get("error")
    except Exception as exc:  # noqa: BLE001 - surfacing automation errors
        status = "failed"
        post_url = None
        error_message = str(exc)

    screenshot_path: Optional[str] = None
    if status in {"need_action", "failed"} and screenshotter is not None:
        screenshot_path = screenshotter(status)

    if status == "posted" and post_url:
        return AvitoPostResult(
            status="POSTED",
            post_url=post_url,
            errors=[],
            step_log=step_log,
            screenshot_path=screenshot_path,
        )

    if status == "need_action":
        return AvitoPostResult(
            status="NEED_ACTION",
            post_url=post_url,
            errors=[error_message or "Manual action required"],
            step_log=step_log,
            screenshot_path=screenshot_path,
        )

    return AvitoPostResult(
        status="FAILED",
        post_url=post_url,
        errors=[error_message or "Posting failed"],
        step_log=step_log,
        screenshot_path=screenshot_path,
    )
